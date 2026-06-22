import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { AgentRunsService } from './agent-runs.service';

@Injectable()
export class AgentRunsScheduler {
  private readonly logger = new Logger(AgentRunsScheduler.name);

  constructor(private readonly agentRunsService: AgentRunsService) {}

  // Market Analyst — 7:30 AM CST / 8:30 AM CDT (13:30 UTC), Mon–Fri
  @Cron('30 13 * * 1-5', { timeZone: 'UTC' })
  async runMarketAnalyst() {
    this.logger.log('Scheduled trigger: market_analyst');
    await this.agentRunsService.trigger('market_analyst');
  }

  // Paper Trader — 8:30 AM CST / 9:30 AM CDT (14:30 UTC), Mon–Fri
  @Cron('30 14 * * 1-5', { timeZone: 'UTC' })
  async runPaperTraderMorning() {
    this.logger.log('Scheduled trigger: paper_trader (morning)');
    await this.agentRunsService.trigger('paper_trader');
  }

  // Paper Trader — 11:00 AM CST / 12:00 PM CDT (17:00 UTC), Mon–Fri
  @Cron('0 17 * * 1-5', { timeZone: 'UTC' })
  async runPaperTraderMidday() {
    this.logger.log('Scheduled trigger: paper_trader (midday)');
    await this.agentRunsService.trigger('paper_trader');
  }

  // Paper Trader — 1:45 PM CST / 2:45 PM CDT (19:45 UTC), Mon–Fri
  @Cron('45 19 * * 1-5', { timeZone: 'UTC' })
  async runPaperTraderAfternoon() {
    this.logger.log('Scheduled trigger: paper_trader (afternoon)');
    await this.agentRunsService.trigger('paper_trader');
  }
}
