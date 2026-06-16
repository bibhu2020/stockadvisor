import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Position } from '../common/entities/position.entity';
import { PortfolioSnapshot } from '../common/entities/portfolio-snapshot.entity';
import { Setting } from '../common/entities/setting.entity';
import { AuthModule } from '../auth/auth.module';
import { PortfolioController } from './portfolio.controller';
import { PortfolioService } from './portfolio.service';

@Module({
  imports: [TypeOrmModule.forFeature([Position, PortfolioSnapshot, Setting]), AuthModule],
  controllers: [PortfolioController],
  providers: [PortfolioService],
})
export class PortfolioModule {}
