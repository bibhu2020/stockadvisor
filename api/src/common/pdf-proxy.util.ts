import type { Response } from 'express';
import * as fs from 'fs';
import * as path from 'path';

// GitHub-hosted artifact — proxy through the server so the bearer token is
// used on the server side (raw.githubusercontent.com requires auth for
// private repos and the browser has no credentials for it). Legacy local
// files are streamed straight from disk.
export async function streamPdf(pdfPath: string, res: Response): Promise<void> {
  if (pdfPath.startsWith('http')) {
    const ghToken = process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN ?? '';
    const reqHeaders: Record<string, string> = ghToken
      ? { Authorization: `token ${ghToken}` }
      : {};
    try {
      const upstream = await fetch(pdfPath, {
        headers: reqHeaders,
        signal: AbortSignal.timeout(30_000),
      });
      if (!upstream.ok) {
        res.status(404).json({ message: 'PDF not available from storage' });
        return;
      }
      const buf = Buffer.from(await upstream.arrayBuffer());
      const filename = pdfPath.split('/').pop() ?? 'report.pdf';
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `inline; filename="${filename}"`);
      res.send(buf);
    } catch {
      res.status(502).json({ message: 'Failed to retrieve PDF from storage' });
    }
    return;
  }

  const absPath = path.isAbsolute(pdfPath)
    ? pdfPath
    : path.join(process.cwd(), '..', pdfPath);

  if (!fs.existsSync(absPath)) {
    res.status(404).json({ message: 'PDF not found' });
    return;
  }
  const filename = path.basename(absPath);
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
  fs.createReadStream(absPath).pipe(res);
}
