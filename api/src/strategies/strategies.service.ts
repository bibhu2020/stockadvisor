import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Strategy } from '../common/entities/strategy.entity';

@Injectable()
export class StrategiesService {
  constructor(@InjectRepository(Strategy) private repo: Repository<Strategy>) {}
  findAll() { return this.repo.find({ order: { created_at: 'DESC' } }); }
  active() { return this.repo.findOne({ where: { is_active: true } }); }
  async findOne(id: number) {
    const s = await this.repo.findOne({ where: { id } });
    if (!s) throw new NotFoundException();
    return s;
  }
}
