import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { AgentRunsService } from './agent-runs.service';

@Injectable()
export class AgentRunsScheduler {
  private readonly logger = new Logger(AgentRunsScheduler.name);

  constructor(private readonly agentRunsService: AgentRunsService) {}

  // Market Analyst — 8:30 AM EST / 9:30 AM EDT (13:30 UTC), Mon–Fri
  // force=true: pre-market research runs before NYSE open; bypass time-window check
  @Cron('30 13 * * 1-5', { timeZone: 'UTC' })
  async runMarketAnalyst() {
    this.logger.log('Scheduled trigger: market_analyst');
    await this.agentRunsService.trigger('market_analyst', true);
  }

  // Paper Trader — 10:30 AM EDT / 9:30 AM EST (14:30 UTC), Mon–Fri
  // force=false: market_hours.py gates on NYSE holidays + time window
  @Cron('30 14 * * 1-5', { timeZone: 'UTC' })
  async runPaperTraderMorning() {
    this.logger.log('Scheduled trigger: paper_trader (morning)');
    await this.agentRunsService.trigger('paper_trader', false);
  }

  // Paper Trader — 1:00 PM EDT / 12:00 PM EST (17:00 UTC), Mon–Fri
  @Cron('0 17 * * 1-5', { timeZone: 'UTC' })
  async runPaperTraderMidday() {
    this.logger.log('Scheduled trigger: paper_trader (midday)');
    await this.agentRunsService.trigger('paper_trader', false);
  }

  // Paper Trader — 3:45 PM EDT / 2:45 PM EST (19:45 UTC), Mon–Fri
  @Cron('45 19 * * 1-5', { timeZone: 'UTC' })
  async runPaperTraderAfternoon() {
    this.logger.log('Scheduled trigger: paper_trader (afternoon)');
    await this.agentRunsService.trigger('paper_trader', false);
  }

  // Retrospective — Mon 5:00 AM UTC = Sun 11:00 PM CST, every week
  // force=false: run_retrospective.py gates to last Sunday of the month
  @Cron('0 5 * * 1', { timeZone: 'UTC' })
  async runRetrospective() {
    this.logger.log('Scheduled trigger: retrospective');
    await this.agentRunsService.trigger('retrospective', false);
  }
}
