/** HERITADE형 대형 콘덴스드 디스플레이 */
const displayEn =
  "font-display text-[clamp(2.75rem,7.2vw,5.25rem)] font-bold uppercase leading-[0.9] tracking-[-0.01em]"

const displayKo = "text-[clamp(1.375rem,3.2vw,2rem)] font-semibold leading-[1.2] tracking-[-0.02em]"

const wordMuted = "text-[#b3b3b3]"
const wordStrong = "text-neutral-900 dark:text-neutral-100"

export function HeritadeHeadline() {
  return (
    <div className="max-w-2xl space-y-6 md:space-y-8">
      <p className={displayKo}>
        <span className={`block ${wordMuted}`}>복잡함은 걷어내고,</span>
        <span className={`block ${wordStrong}`}>확장은 자유롭게.</span>
      </p>

      <h1 className={`space-y-0 ${displayEn}`}>
        <span className="block text-pretty">
          <span className={wordMuted}>Simplify</span>{" "}
          <span className={wordStrong}>Complexity,</span>
        </span>
        <span className="block text-pretty">
          <span className={wordMuted}>Scale</span>{" "}
          <span className={wordStrong}>Without Limits.</span>
        </span>
      </h1>
    </div>
  )
}
