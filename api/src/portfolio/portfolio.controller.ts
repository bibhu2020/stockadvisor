import { Controller, Get, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { PortfolioService } from './portfolio.service';

@Controller('portfolio')
@UseGuards(JwtAuthGuard)
export class PortfolioController {
  constructor(private svc: PortfolioService) {}
  @Get('current') current() { return this.svc.current(); }
  @Get('history') history() { return this.svc.history(); }
}
