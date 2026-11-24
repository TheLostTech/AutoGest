plugins {
    id("com.android.application")
}

// Indirizzo con cui l'app parte la prima volta (poi si cambia dall'app inquadrando il QR di scripts/piazzale-test.sh).
// Si passa alla compilazione: ./gradlew assembleDebug -Ppiazzale.indirizzo=https://….trycloudflare.com
val indirizzo = (findProperty("piazzale.indirizzo") as String?)?.trimEnd('/') ?: ""

android {
    namespace = "it.lostar.piazzale"
    compileSdk = 36

    defaultConfig {
        applicationId = "it.lostar.piazzale"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1-test"
        buildConfigField("String", "INDIRIZZO", "\"$indirizzo\"")
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.core:core:1.17.0")
    implementation("androidx.webkit:webkit:1.14.0")
    // Lettore QR di Google Play Services: niente permesso fotocamera, schermata già fatta
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
}
