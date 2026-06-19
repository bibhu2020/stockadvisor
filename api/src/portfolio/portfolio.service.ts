import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { MoreThan, Repository } from 'typeorm';
import { Position } from '../common/entities/position.entity';
import { PortfolioSnapshot } from '../common/entities/portfolio-snapshot.entity';
import { Setting } from '../common/entities/setting.entity';

@Injectable()
export class PortfolioService {
  constructor(
    @InjectRepository(Position) private positions: Repository<Position>,
    @InjectRepository(PortfolioSnapshot) private snapshots: Repository<PortfolioSnapshot>,
    @InjectRepository(Setting) private settings: Repository<Setting>,
  ) {}

  async current() {
    const bpSetting = await this.settings.findOne({ where: { key: 'buying_power' } });
    const buying_power = bpSetting ? +bpSetting.value : 5000;
    const open = await this.positions.find({ where: { status: 'open', quantity: MoreThan(0) } });
    return { buying_power, open_positions: open };
  }

  history() {
    return this.snapshots.find({ order: { snapshot_at: 'ASC' }, take: 200 });
  }
}
