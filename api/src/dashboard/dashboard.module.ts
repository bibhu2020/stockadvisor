import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Transaction } from '../common/entities/transaction.entity';
import { PortfolioSnapshot } from '../common/entities/portfolio-snapshot.entity';
import { AuthModule } from '../auth/auth.module';
import { AgentRunsModule } from '../agent-runs/agent-runs.module';
import { DashboardController } from './dashboard.controller';
import { DashboardService } from './dashboard.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([Transaction, PortfolioSnapshot]),
    AuthModule,
    AgentRunsModule,
  ],
  controllers: [DashboardController],
  providers: [DashboardService],
})
export class DashboardModule {}
