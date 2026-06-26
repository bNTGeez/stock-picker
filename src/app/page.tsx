export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 dark:bg-zinc-950 font-sans">
      <main className="flex flex-col items-center gap-6 text-center px-6">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          AI Investment Research Analyst
        </h1>
        <p className="max-w-md text-lg text-zinc-500 dark:text-zinc-400">
          Evidence-backed investment memos with structured variant hypotheses,
          adversarial research, and reverse DCF expectations.
        </p>
        <span className="text-sm text-zinc-400 dark:text-zinc-600">
          Dashboard coming soon
        </span>
      </main>
    </div>
  );
}
