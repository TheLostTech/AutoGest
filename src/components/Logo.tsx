// Marchio AutoLost: nome nel carattere stretto delle etichette, A e L più grandi delle altre lettere,
// "Auto" grigio e "Lost" giallo come il marchio Lostar. La dimensione si regola con la grandezza del testo.
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`code inline-block font-extrabold uppercase leading-none tracking-[0.02em] ${className}`}>
      <span className="text-[#C3C8D0]">
        A<span className="text-[0.76em]">uto</span>
      </span>
      <span className="text-[#F4B500]">
        L<span className="text-[0.76em]">ost</span>
      </span>
    </span>
  );
}
