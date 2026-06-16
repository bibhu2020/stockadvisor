import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { IsNull, Or, Repository } from 'typeorm';
import { Notification } from '../common/entities/notification.entity';

@Injectable()
export class NotificationsService {
  constructor(@InjectRepository(Notification) private repo: Repository<Notification>) {}

  findForUser(userId: number) {
    return this.repo.find({
      where: [{ user_id: userId }, { user_id: IsNull() }],
      order: { created_at: 'DESC' },
      take: 50,
    });
  }

  async unreadCount(userId: number): Promise<{ count: number }> {
    const count = await this.repo.count({
      where: [
        { user_id: userId, is_read: false },
        { user_id: IsNull(), is_read: false },
      ],
    });
    return { count };
  }

  async markRead(id: number, userId: number) {
    await this.repo.update(id, { is_read: true });
    return { message: 'Marked read' };
  }

  async markAllRead(userId: number) {
    await this.repo
      .createQueryBuilder()
      .update()
      .set({ is_read: true })
      .where('user_id = :uid OR user_id IS NULL', { uid: userId })
      .execute();
    return { message: 'All marked read' };
  }
}
