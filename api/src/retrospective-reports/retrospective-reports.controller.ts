import {
  Controller,
  Get,
  Param,
  Query,
  Res,
  UnauthorizedException,
  UseGuards,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import type { Response } from 'express';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { streamPdf } from '../common/pdf-proxy.util';
import { RetrospectiveReportsService } from './retrospective-reports.service';

@Controller('retrospective-reports')
export class RetrospectiveReportsController {
  constructor(
    private svc: RetrospectiveReportsService,
    private jwt: JwtService,
  ) {}

  @Get()
  @UseGuards(JwtAuthGuard)
  findAll() {
    return this.svc.findAll();
  }

  @Get(':id')
  @UseGuards(JwtAuthGuard)
  findOne(@Param('id') id: string) {
    return this.svc.findOne(+id);
  }

  // Token verified manually from ?token= so a plain <a href> works without an
  // Authorization header.
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
    await streamPdf(pdfPath, res);
  }
}
