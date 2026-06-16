import { Controller, Get, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { DashboardService } from './dashboard.service';

@Controller('dashboard')
@UseGuards(JwtAuthGuard)
export class DashboardController {
  constructor(private svc: DashboardService) {}
  @Get('monthly-pnl')      monthlyPnl()       { return this.svc.monthlyPnl(); }
  @Get('portfolio-value')  portfolioHistory()  { return this.svc.portfolioHistory(); }
  @Get('win-rate')         winRate()           { return this.svc.winRate(); }
  @Get('sector-breakdown') sectorBreakdown()   { return this.svc.sectorBreakdown(); }
  @Get('agent-status')     agentStatus()       { return this.svc.agentStatus(); }
}
