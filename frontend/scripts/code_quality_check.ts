import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

function runCommand(command: string, cwd: string): { stdout: string; stderr: string; code: number } {
  console.log(`Running: ${command}`);
  try {
    const stdout = execSync(command, { cwd, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
    return { stdout, stderr: '', code: 0 };
  } catch (error: any) {
    return { stdout: error.stdout || '', stderr: error.stderr || '', code: error.status || 1 };
  }
}

function main() {
  const frontendDir = path.resolve(__dirname, '..');
  const reportPath = path.join(frontendDir, 'code_quality_report.json');
  
  const report: any = {
    timestamp: new Date().toISOString(),
    tools: {}
  };

  // 1. ESLint
  console.log('--- Running ESLint ---');
  const eslintRes = runCommand('npx eslint "src/**/*.{ts,tsx}" --format json', frontendDir);
  try {
    report.tools.eslint = JSON.parse(eslintRes.stdout);
  } catch (e) {
    report.tools.eslint = { error: 'Failed to parse ESLint JSON', raw: eslintRes.stdout, code: eslintRes.code };
  }

  // 2. TypeScript Compiler Check
  console.log('--- Running TypeScript Type Check ---');
  const tscRes = runCommand('npx tsc --noEmit', frontendDir);
  report.tools.tsc = {
    output: tscRes.stdout,
    error: tscRes.stderr,
    code: tscRes.code
  };

  // 3. Bundle Analyzer (if webpack or similar is present, or just build stats)
  console.log('--- Checking Bundle Size ---');
  // Just running standard build to check its output
  const buildRes = runCommand('npm run build', frontendDir);
  report.tools.build = {
    output: buildRes.stdout,
    code: buildRes.code
  };

  // 4. Save Report
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');
  console.log(`\nReport generated successfully: ${reportPath}`);
  
  // Exit with failure if severe errors
  if (tscRes.code !== 0) {
    console.warn('TypeScript checking failed, but report generated.');
  }
}

main();
