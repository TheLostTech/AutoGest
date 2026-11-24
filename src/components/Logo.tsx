// Marchio Piazzale: nome nel carattere stretto delle etichette, P più grande delle altre lettere,
// "Piazz" grigio e "ale" giallo come il marchio Lostar. La dimensione si regola con la grandezza del testo.
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`code inline-block font-extrabold uppercase leading-none tracking-[0.02em] ${className}`}>
      <span className="text-[#C3C8D0]">
        P<span className="text-[0.76em]">iazz</span>
      </span>
      <span className="text-[0.76em] text-[#F4B500]">ale</span>
    </span>
  );
}
