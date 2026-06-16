import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { AgentRun } from '../common/entities/agent-run.entity';

@Injectable()
export class AgentRunsService {
  constructor(@InjectRepository(AgentRun) private repo: Repository<AgentRun>) {}

  findAll(type?: string, status?: string) {
    const where: Partial<AgentRun> = {};
    if (type) where.agent_type = type;
    if (status) where.status = status;
    return this.repo.find({ where, order: { id: 'DESC' }, take: 100 });
  }

  findOne(id: number) {
    return this.repo.findOne({ where: { id } });
  }

  async getLogSince(id: number, offset: number): Promise<string> {
    const run = await this.repo.findOne({ where: { id }, select: { log: true, status: true } });
    if (!run) return '';
    return (run.log ?? '').slice(offset);
  }

  async trigger(agentType: string): Promise<{ message: string }> {
    const workflows: Record<string, string> = {
      market_analyst: 'market_analyst.yml',
      paper_trader:   'paper_trader.yml',
      retrospective:  'retrospective.yml',
    };
    const workflow = workflows[agentType];
    if (!workflow) return { message: 'Unknown agent type' };

    const token = process.env.GITHUB_TOKEN;
    const repo  = process.env.GITHUB_REPO ?? 'bibhu2020/stockadvisor';
    if (!token) return { message: 'GITHUB_TOKEN not configured — cannot dispatch workflow' };

    const url = `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: 'main', inputs: { force: 'true' } }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`GitHub dispatch failed: ${res.status} — ${text}`);
    }

    return { message: `${agentType} workflow dispatched (force=true)` };
  }

  async kill(id: number): Promise<{ ok: boolean; message: string }> {
    const run = await this.repo.findOne({ where: { id } });
    if (!run) return { ok: false, message: 'Run not found' };
    if (run.status !== 'running' && run.status !== 'pending')
      return { ok: false, message: `Run is already ${run.status}` };
    await this.repo.update(id, {
      status: 'failed',
      finished_at: new Date(),
      error: 'Killed by user via UI',
    });
    return { ok: true, message: `Run #${id} killed` };
  }

  lastRunByType(): Promise<(AgentRun | null)[]> {
    return this.repo
      .createQueryBuilder('r')
      .select('r.agent_type', 'agent_type')
      .addSelect('MAX(r.id)', 'last_id')
      .groupBy('r.agent_type')
      .getRawMany()
      .then(async (rows: { agent_type: string; last_id: number }[]) => {
        const result: (AgentRun | null)[] = [];
        for (const row of rows) {
          const run = await this.repo.findOne({ where: { id: row.last_id } });
          result.push(run);
        }
        return result;
      });
  }
}
