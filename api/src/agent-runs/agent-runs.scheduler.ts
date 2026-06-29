import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import * as cron from 'node-cron';
import { AgentRunsService } from './agent-runs.service';

@Injectable()
export class AgentRunsScheduler implements OnModuleInit {
  private readonly logger = new Logger(AgentRunsScheduler.name);

  constructor(private readonly agentRunsService: AgentRunsService) {}

  onModuleInit() {
    // Market Analyst — 8:30 AM EST / 9:30 AM EDT (13:30 UTC), Mon–Fri
    // force=true: pre-market research, bypass NYSE time-window check
    cron.schedule('30 13 * * 1-5', () => this.dispatch('market_analyst', true), { timezone: 'UTC' });

    // Paper Trader — 9:30 AM EST / 10:30 AM EDT (14:30 UTC), Mon–Fri
    cron.schedule('30 14 * * 1-5', () => this.dispatch('paper_trader', false), { timezone: 'UTC' });

    // Paper Trader — 12:00 PM EST / 1:00 PM EDT (17:00 UTC), Mon–Fri
    cron.schedule('0 17 * * 1-5', () => this.dispatch('paper_trader', false), { timezone: 'UTC' });

    // Paper Trader — 2:45 PM EST / 3:45 PM EDT (19:45 UTC), Mon–Fri
    cron.schedule('45 19 * * 1-5', () => this.dispatch('paper_trader', false), { timezone: 'UTC' });

    // Retrospective — Mon 4:00 AM UTC (= Sun 11:00 PM CDT / 10:00 PM CST)
    // force=false: run_retrospective.py gates to last Sunday of the month
    cron.schedule('0 4 * * 1', () => this.dispatch('retrospective', false), { timezone: 'UTC' });

    this.logger.log('Agent cron schedules registered');
  }

  private async dispatch(agentType: string, force: boolean) {
    this.logger.log(`Scheduled trigger: ${agentType} (force=${force})`);
    try {
      await this.agentRunsService.trigger(agentType, force, 'scheduled');
    } catch (err) {
      this.logger.error(`Scheduled dispatch failed for ${agentType}: ${err}`);
    }
  }
}
