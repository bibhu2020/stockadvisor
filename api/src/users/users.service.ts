import { ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../common/entities/user.entity';

@Injectable()
export class UsersService {
  constructor(@InjectRepository(User) private repo: Repository<User>) {}

  findAll() {
    return this.repo.find({ select: { id: true, email: true, name: true, role: true, approved_at: true, created_at: true } });
  }

  async approve(id: number) {
    const user = await this.repo.findOne({ where: { id } });
    if (!user) throw new NotFoundException();
    user.role = 'guest';
    user.approved_at = new Date();
    await this.repo.save(user);
    return { message: 'User approved', user };
  }

  async setRole(id: number, role: string) {
    if (!['admin', 'guest', 'pending'].includes(role)) throw new ForbiddenException('Invalid role');
    const user = await this.repo.findOne({ where: { id } });
    if (!user) throw new NotFoundException();
    user.role = role;
    if (role !== 'pending') user.approved_at = new Date();
    await this.repo.save(user);
    return { message: 'Role updated', user };
  }
}
