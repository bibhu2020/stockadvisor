import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AgentRun } from '../common/entities/agent-run.entity';
import { AuthModule } from '../auth/auth.module';
import { AgentRunsController } from './agent-runs.controller';
import { AgentRunsScheduler } from './agent-runs.scheduler';
import { AgentRunsService } from './agent-runs.service';

@Module({
  imports: [TypeOrmModule.forFeature([AgentRun]), AuthModule],
  controllers: [AgentRunsController],
  providers: [AgentRunsService, AgentRunsScheduler],
  exports: [AgentRunsService],
})
export class AgentRunsModule {}
