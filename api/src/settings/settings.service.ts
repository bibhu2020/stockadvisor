import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Setting } from '../common/entities/setting.entity';

@Injectable()
export class SettingsService {
  constructor(@InjectRepository(Setting) private repo: Repository<Setting>) {}

  findAll() { return this.repo.find(); }

  async update(updates: Record<string, string>) {
    for (const [key, value] of Object.entries(updates)) {
      await this.repo.upsert({ key, value: String(value) }, ['key']);
    }
    return this.repo.find();
  }
}
