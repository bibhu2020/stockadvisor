import { Controller, Get, Param, Query, Res, UnauthorizedException, UseGuards } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import type { Response } from 'express';
import * as fs from 'fs';
import * as path from 'path';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { ReportsService } from './reports.service';

@Controller('reports')
export class ReportsController {
  constructor(private svc: ReportsService, private jwt: JwtService) {}

  @Get()
  @UseGuards(JwtAuthGuard)
  findAll() { return this.svc.findAll(); }

  @Get(':id')
  @UseGuards(JwtAuthGuard)
  findOne(@Param('id') id: string) { return this.svc.findOne(+id); }

  // Token verified manually from ?token= so a plain <a href> works without an
  // Authorization header. For GitHub-hosted PDFs we redirect; for legacy local
  // files we stream from disk.
  @Get(':id/pdf')
  async pdf(
    @Param('id') id: string,
    @Query('token') token: string,
    @Res() res: Response,
  ) {
    try {
      this.jwt.verify(token);
    } catch {
      throw new UnauthorizedException('Invalid or missing token');
    }

    const pdfPath = await this.svc.getPdfPath(+id);

    // GitHub-hosted artifact — proxy through the server so the bearer token
    // is used on the server side (raw.githubusercontent.com requires auth for
    // private repos and the browser has no credentials for it).
    if (pdfPath.startsWith('http')) {
      const ghToken = process.env.GITHUB_TOKEN ?? '';
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

    // Legacy: stream from local disk
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
}
