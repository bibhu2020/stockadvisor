import {
  Controller, ForbiddenException, Get, Param, Patch, Post, Query,
  Request, Res, UseGuards
} from '@nestjs/common';
import type { Response } from 'express';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { AgentRunsService } from './agent-runs.service';

@Controller('agent-runs')
@UseGuards(JwtAuthGuard)
export class AgentRunsController {
  constructor(private svc: AgentRunsService) {}

  @Get()
  findAll(
    @Query('type') type?: string,
    @Query('status') status?: string,
  ) {
    return this.svc.findAll(type, status);
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.svc.findOne(+id);
  }

  @Get(':id/stream')
  async stream(@Param('id') id: string, @Res() res: Response) {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    let offset = 0;
    const timer = setInterval(async () => {
      const chunk = await this.svc.getLogSince(+id, offset);
      if (chunk) {
        offset += chunk.length;
        res.write(`data: ${JSON.stringify({ log: chunk })}\n\n`);
      }
      const run = await this.svc.findOne(+id);
      if (!run || ['completed', 'failed'].includes(run.status)) {
        res.write(`data: ${JSON.stringify({ done: true, status: run?.status })}\n\n`);
        clearInterval(timer);
        res.end();
      }
    }, 500);

    res.on('close', () => clearInterval(timer));
  }

  @Patch(':id/kill')
  kill(
    @Param('id') id: string,
    @Request() req: { user: { role: string } },
  ) {
    if (req.user.role !== 'admin') throw new ForbiddenException();
    return this.svc.kill(+id);
  }

  @Post('trigger/:type')
  trigger(
    @Param('type') type: string,
    @Request() req: { user: { role: string } },
  ) {
    if (req.user.role !== 'admin') throw new ForbiddenException();
    return this.svc.trigger(type, true, 'manual');
  }
}
