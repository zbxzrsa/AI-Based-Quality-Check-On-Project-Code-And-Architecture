export default function Home() {
    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-24">
            <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
                <h1 className="mb-8 text-center text-4xl font-bold text-slate-900 dark:text-white">
                    AI Code Review Platform
                </h1>
                <div className="mb-8 grid gap-4 text-center lg:mb-0 lg:w-full lg:max-w-5xl lg:grid-cols-3 lg:text-left">
                    <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
                        <h2 className="mb-3 text-2xl font-semibold">
                            Dashboard{' '}
                            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                                -&gt;
                            </span>
                        </h2>
                        <p className="m-0 max-w-[30ch] text-sm opacity-50">
                            View your code review analytics and insights
                        </p>
                    </div>

                    <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
                        <h2 className="mb-3 text-2xl font-semibold">
                            Projects{' '}
                            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                                -&gt;
                            </span>
                        </h2>
                        <p className="m-0 max-w-[30ch] text-sm opacity-50">
                            Manage your connected repositories and projects
                        </p>
                    </div>

                    <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
                        <h2 className="mb-3 text-2xl font-semibold">
                            Analysis{' '}
                            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                                -&gt;
                            </span>
                        </h2>
                        <p className="m-0 max-w-[30ch] text-sm opacity-50">
                            Explore code architecture and dependency graphs
                        </p>
                    </div>
                </div>
            </div>
        </main>
    );
}
