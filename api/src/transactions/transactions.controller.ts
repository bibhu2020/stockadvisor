import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { TransactionsService } from './transactions.service';

@Controller('transactions')
@UseGuards(JwtAuthGuard)
export class TransactionsController {
  constructor(private svc: TransactionsService) {}

  @Get()
  findAll(
    @Query('symbol') symbol?: string,
    @Query('action') action?: string,
    @Query('from') from?: string,
    @Query('to') to?: string,
    @Query('strategy_id') strategy_id?: string,
    @Query('pnl') pnl?: 'gain' | 'loss' | 'all',
  ) {
    return this.svc.findAll({ symbol, action, from, to, strategy_id, pnl });
  }

  @Get('summary')
  summary() { return this.svc.summary(); }

  @Get('market-prices')
  marketPrices(@Query('symbols') symbols: string) {
    const list = symbols ? symbols.split(',').filter(Boolean) : [];
    return this.svc.getMarketPrices(list);
  }
}
