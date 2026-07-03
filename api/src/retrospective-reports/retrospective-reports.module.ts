import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AuthModule } from '../auth/auth.module';
import { RetrospectiveReport } from '../common/entities/retrospective-report.entity';
import { RetrospectiveReportsController } from './retrospective-reports.controller';
import { RetrospectiveReportsService } from './retrospective-reports.service';

@Module({
  imports: [TypeOrmModule.forFeature([RetrospectiveReport]), AuthModule],
  controllers: [RetrospectiveReportsController],
  providers: [RetrospectiveReportsService],
})
export class RetrospectiveReportsModule {}
