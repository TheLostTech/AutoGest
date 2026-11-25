package it.lostar.piazzale;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.provider.MediaStore;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import android.window.OnBackInvokedDispatcher;

import androidx.core.content.FileProvider;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.webkit.ScriptHandler;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;

import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions;
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning;

import java.io.File;
import java.util.Collections;

/**
 * Piazzale per Android: il gestionale web in una finestra a tutto schermo, con quello che il browser
 * dentro un'app non fa da solo: fotocamera per la scansione, foto dai moduli, stampa delle etichette,
 * PDF scaricati, tasto Indietro. L'indirizzo del server si cambia inquadrando il QR di scripts/piazzale-test.sh.
 */
public class MainActivity extends Activity {
    private static final int PERMESSO_FOTOCAMERA_WEB = 1;
    private static final int PERMESSO_FOTOCAMERA_FOTO = 2;
    private static final int SCELTA_FILE = 10;
    private static final String AZIONE_CAMBIA_SERVER = "it.lostar.piazzale.CAMBIA_SERVER";
    // window.print() dentro un'app non fa nulla: lo si passa alla stampa di Android
    private static final String SCRIPT_STAMPA =
            "(function(){if(window.PiazzaleApp){window.print=function(){PiazzaleApp.stampa(document.title||'Piazzale');};}})();";

    private WebView web;
    private View impostazioni;
    private TextView messaggio;
    private EditText campo;
    private ProgressBar caricamento;
    private SharedPreferences prefs;

    private boolean scriptAllAvvio;
    private ScriptHandler scriptStampa;
    private PermissionRequest permessoInAttesa;
    private ValueCallback<Uri[]> fileInAttesa;
    private WebChromeClient.FileChooserParams parametriInAttesa;
    private Uri fotoScattata;
    private long ultimoIndietro;

    @Override
    protected void onCreate(Bundle stato) {
        super.onCreate(stato);
        setContentView(R.layout.principale);
        prefs = getSharedPreferences("piazzale", MODE_PRIVATE);
        web = findViewById(R.id.web);
        impostazioni = findViewById(R.id.impostazioni);
        messaggio = findViewById(R.id.messaggio);
        campo = findViewById(R.id.indirizzo);
        caricamento = findViewById(R.id.caricamento);

        // Da Android 15 l'app disegna sotto le barre di sistema: si lascia spazio a barre e tastiera
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        View radice = findViewById(R.id.radice);
        ViewCompat.setOnApplyWindowInsetsListener(radice, (v, ins) -> {
            Insets i = ins.getInsets(WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.ime() | WindowInsetsCompat.Type.displayCutout());
            v.setPadding(i.left, i.top, i.right, i.bottom);
            return WindowInsetsCompat.CONSUMED;
        });

        preparaWeb();

        findViewById(R.id.qr).setOnClickListener(v -> leggiQr());
        findViewById(R.id.apri).setOnClickListener(v -> apriDaCampo());
        campo.setOnEditorActionListener((v, azione, e) -> {
            if (azione == EditorInfo.IME_ACTION_GO) {
                apriDaCampo();
                return true;
            }
            return false;
        });

        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::indietro);
        }

        avvia(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (AZIONE_CAMBIA_SERVER.equals(intent.getAction())) mostraImpostazioni("Indirizzo del server di Piazzale.");
    }

    private void avvia(Intent intent) {
        String indirizzo = indirizzo();
        if (AZIONE_CAMBIA_SERVER.equals(intent.getAction())) {
            mostraImpostazioni("Indirizzo del server di Piazzale.");
        } else if (indirizzo.isEmpty()) {
            mostraImpostazioni("Benvenuto. Inquadra il QR che il Mac mostra quando apre l'ambiente di prova.");
        } else {
            apri(indirizzo);
        }
    }

    // ---------- Finestra web ----------

    private void preparaWeb() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setUserAgentString(s.getUserAgentString() + " PiazzaleApp/" + BuildConfig.VERSION_NAME);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);

        web.addJavascriptInterface(new Ponte(), "PiazzaleApp");
        scriptAllAvvio = WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT);
        registraScriptStampa();

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                // Dentro l'app solo il nostro server: ogni altro sito (WhatsApp compreso) si apre fuori,
                // così nessuna pagina estranea riceve la fotocamera o il ponte di stampa
                Uri u = r.getUrl();
                if (stessoServer(u)) return false;
                apriFuori(u.toString());
                return true;
            }

            @Override
            public void onPageStarted(WebView v, String url, android.graphics.Bitmap icona) {
                caricamento.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView v, String url) {
                caricamento.setVisibility(View.GONE);
                if (!scriptAllAvvio && stessoServer(Uri.parse(url))) v.evaluateJavascript(SCRIPT_STAMPA, null);
            }

            @Override
            public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {
                if (r.isForMainFrame()) serverAssente(String.valueOf(e.getDescription()));
            }

            @Override
            public void onReceivedHttpError(WebView v, WebResourceRequest r, WebResourceResponse risposta) {
                // 502 e 530: risponde Cloudflare, ma il Mac dietro il collegamento è spento o il collegamento è chiuso
                int c = risposta.getStatusCode();
                if (r.isForMainFrame() && (c == 502 || c == 530)) serverAssente("errore " + c);
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest richiesta) {
                runOnUiThread(() -> permessoFotocameraWeb(richiesta));
            }

            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileInAttesa != null) fileInAttesa.onReceiveValue(null);
                fileInAttesa = cb;
                parametriInAttesa = p;
                if (p.isCaptureEnabled() && accettaImmagini(p)) scatta();
                else scegliFile();
                return true;
            }
        });

        web.setDownloadListener((url, agente, disposizione, tipo, lunghezza) -> scarica(url, agente, disposizione, tipo));
    }

    private void serverAssente(String dettaglio) {
        mostraImpostazioni("Il server non risponde (" + dettaglio + ").\n\nÈ acceso il Mac con l'ambiente di prova? "
                + "Se l'indirizzo è cambiato, inquadra il QR nuovo.");
    }

    // ---------- Indirizzo del server ----------

    private String indirizzo() {
        return prefs.getString("indirizzo", BuildConfig.INDIRIZZO);
    }

    private static String normalizza(String testo) {
        if (testo == null) return null;
        String t = testo.trim();
        if (t.isEmpty()) return null;
        if (t.startsWith("http://")) return null; // solo https: Android blocca comunque il traffico in chiaro
        if (!t.startsWith("https://")) t = "https://" + t;
        Uri u = Uri.parse(t);
        if (u.getHost() == null || u.getHost().isEmpty()) return null;
        return u.getScheme() + "://" + u.getEncodedAuthority();
    }

    // Stessa origine del server impostato (schema, host e porta)
    private boolean stessoServer(Uri u) {
        if (u == null || u.getScheme() == null || u.getEncodedAuthority() == null) return false;
        String origine = u.getScheme().toLowerCase(java.util.Locale.ROOT) + "://" + u.getEncodedAuthority().toLowerCase(java.util.Locale.ROOT);
        return origine.equals(indirizzo().toLowerCase(java.util.Locale.ROOT));
    }

    // Lo script che collega window.print alla stampa di Android vale solo per il server impostato
    private void registraScriptStampa() {
        if (!scriptAllAvvio) return;
        if (scriptStampa != null) scriptStampa.remove();
        scriptStampa = WebViewCompat.addDocumentStartJavaScript(web, SCRIPT_STAMPA, Collections.singleton(indirizzo()));
    }

    private void apri(String base) {
        prefs.edit().putString("indirizzo", base).apply();
        registraScriptStampa();
        impostazioni.setVisibility(View.GONE);
        web.loadUrl(base + "/");
    }

    private void apriDaCampo() {
        String base = normalizza(campo.getText().toString());
        if (base == null) {
            Toast.makeText(this, "Indirizzo non valido", Toast.LENGTH_SHORT).show();
            return;
        }
        apri(base);
    }

    private void mostraImpostazioni(String testo) {
        caricamento.setVisibility(View.GONE);
        messaggio.setText(testo);
        campo.setText(indirizzo());
        impostazioni.setVisibility(View.VISIBLE);
    }

    private void leggiQr() {
        GmsBarcodeScannerOptions opzioni = new GmsBarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build();
        GmsBarcodeScanning.getClient(this, opzioni).startScan()
                .addOnSuccessListener(codice -> {
                    String base = normalizza(codice.getRawValue());
                    if (base == null) {
                        Toast.makeText(this, "Questo QR non contiene un indirizzo", Toast.LENGTH_LONG).show();
                        return;
                    }
                    apri(base);
                })
                .addOnFailureListener(e -> Toast.makeText(this, "Lettore QR non disponibile: scrivi l'indirizzo", Toast.LENGTH_LONG).show());
    }

    // ---------- Fotocamera per la scansione (getUserMedia) ----------

    private boolean haFotocamera() {
        return checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    private void permessoFotocameraWeb(PermissionRequest richiesta) {
        if (!stessoServer(richiesta.getOrigin())) {
            richiesta.deny();
            return;
        }
        boolean video = false;
        for (String r : richiesta.getResources()) if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(r)) video = true;
        if (!video) {
            richiesta.deny();
            return;
        }
        if (haFotocamera()) {
            richiesta.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
        } else {
            if (permessoInAttesa != null) permessoInAttesa.deny();
            permessoInAttesa = richiesta;
            requestPermissions(new String[]{Manifest.permission.CAMERA}, PERMESSO_FOTOCAMERA_WEB);
        }
    }

    // ---------- Foto e file dai moduli (<input type="file">) ----------

    private static boolean accettaImmagini(WebChromeClient.FileChooserParams p) {
        String[] tipi = p.getAcceptTypes();
        if (tipi == null || tipi.length == 0) return true;
        for (String t : tipi) if (t.isEmpty() || t.startsWith("image/")) return true;
        return false;
    }

    private Intent intentFotocamera() {
        File cartella = new File(getCacheDir(), "foto");
        //noinspection ResultOfMethodCallIgnored
        cartella.mkdirs();
        File f = new File(cartella, "foto-" + System.currentTimeMillis() + ".jpg");
        fotoScattata = FileProvider.getUriForFile(this, getPackageName() + ".foto", f);
        Intent i = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        i.putExtra(MediaStore.EXTRA_OUTPUT, fotoScattata);
        i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        return i;
    }

    private void scatta() {
        if (!haFotocamera()) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, PERMESSO_FOTOCAMERA_FOTO);
            return;
        }
        try {
            startActivityForResult(intentFotocamera(), SCELTA_FILE);
        } catch (ActivityNotFoundException e) {
            scegliFile();
        }
    }

    private void scegliFile() {
        fotoScattata = null;
        Intent scelta = parametriInAttesa.createIntent();
        if (parametriInAttesa.getMode() == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE) {
            scelta.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        }
        Intent finestra = Intent.createChooser(scelta, "Scegli");
        if (accettaImmagini(parametriInAttesa) && haFotocamera()) {
            finestra.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{intentFotocamera()});
        }
        try {
            startActivityForResult(finestra, SCELTA_FILE);
        } catch (ActivityNotFoundException e) {
            fileInAttesa.onReceiveValue(null);
            fileInAttesa = null;
        }
    }

    @Override
    protected void onActivityResult(int codice, int esito, Intent dati) {
        super.onActivityResult(codice, esito, dati);
        if (codice != SCELTA_FILE || fileInAttesa == null) return;
        Uri[] scelti = null;
        if (esito == RESULT_OK) {
            ClipData clip = dati == null ? null : dati.getClipData();
            if (clip != null && clip.getItemCount() > 0) {
                scelti = new Uri[clip.getItemCount()];
                for (int i = 0; i < clip.getItemCount(); i++) scelti[i] = clip.getItemAt(i).getUri();
            } else if (dati != null && dati.getData() != null) {
                scelti = new Uri[]{dati.getData()};
            } else if (fotoScattata != null) {
                scelti = new Uri[]{fotoScattata};
            }
        }
        fileInAttesa.onReceiveValue(scelti);
        fileInAttesa = null;
        fotoScattata = null;
    }

    @Override
    public void onRequestPermissionsResult(int codice, String[] permessi, int[] esiti) {
        super.onRequestPermissionsResult(codice, permessi, esiti);
        boolean concesso = esiti.length > 0 && esiti[0] == PackageManager.PERMISSION_GRANTED;
        if (codice == PERMESSO_FOTOCAMERA_WEB && permessoInAttesa != null) {
            if (concesso) permessoInAttesa.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
            else permessoInAttesa.deny();
            permessoInAttesa = null;
        } else if (codice == PERMESSO_FOTOCAMERA_FOTO && fileInAttesa != null) {
            if (concesso) scatta();
            else scegliFile();
        }
    }

    // ---------- PDF e altri file scaricati ----------

    private void scarica(String url, String agente, String disposizione, String tipo) {
        if (!url.startsWith("http")) {
            Toast.makeText(this, "Questo file non si può scaricare dall'app", Toast.LENGTH_LONG).show();
            return;
        }
        try {
            String nome = URLUtil.guessFileName(url, disposizione, tipo);
            DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
            String cookie = CookieManager.getInstance().getCookie(url);
            if (cookie != null) r.addRequestHeader("Cookie", cookie);
            r.addRequestHeader("User-Agent", agente);
            r.setMimeType(tipo);
            r.setTitle(nome);
            r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, nome);
            r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            getSystemService(DownloadManager.class).enqueue(r);
            Toast.makeText(this, "Scarico " + nome + ": lo trovi nelle notifiche", Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Scaricamento non riuscito", Toast.LENGTH_LONG).show();
        }
    }

    // Fuori dall'app vanno solo questi schemi (WhatsApp passa da https://wa.me).
    // Niente "intent:": una pagina potrebbe usarlo per aprire componenti di questa o di altre app con permessi sui file.
    private static final java.util.Set<String> SCHEMI_FUORI = new java.util.HashSet<>(java.util.Arrays.asList("http", "https", "tel", "mailto", "sms", "smsto", "geo"));

    private void apriFuori(String url) {
        try {
            Uri u = Uri.parse(url);
            String schema = u.getScheme() == null ? "" : u.getScheme().toLowerCase(java.util.Locale.ROOT);
            if (!SCHEMI_FUORI.contains(schema)) {
                Toast.makeText(this, "Collegamento non supportato", Toast.LENGTH_SHORT).show();
                return;
            }
            Intent i = new Intent(Intent.ACTION_VIEW, u);
            i.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(i);
        } catch (Exception e) {
            Toast.makeText(this, "Nessuna app per aprirlo", Toast.LENGTH_SHORT).show();
        }
    }

    // ---------- Stampa ----------

    private class Ponte {
        @JavascriptInterface
        public void stampa(String titolo) {
            runOnUiThread(() -> {
                if (web.getUrl() == null || !stessoServer(Uri.parse(web.getUrl()))) return;
                String nome = titolo == null || titolo.isEmpty() ? "Piazzale" : titolo;
                PrintManager pm = getSystemService(PrintManager.class);
                pm.print(nome, web.createPrintDocumentAdapter(nome), new PrintAttributes.Builder().build());
            });
        }
    }

    // ---------- Indietro ----------

    private void indietro() {
        if (impostazioni.getVisibility() == View.VISIBLE && web.getUrl() != null) {
            impostazioni.setVisibility(View.GONE);
        } else if (web.canGoBack()) {
            web.goBack();
        } else if (System.currentTimeMillis() - ultimoIndietro < 2000) {
            finish();
        } else {
            ultimoIndietro = System.currentTimeMillis();
            Toast.makeText(this, "Premi ancora Indietro per uscire", Toast.LENGTH_SHORT).show();
        }
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        indietro();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }

    @Override
    protected void onPause() {
        web.onPause();
        CookieManager.getInstance().flush();
        super.onPause();
    }
}
