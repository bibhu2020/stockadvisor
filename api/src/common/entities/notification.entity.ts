import { Column, CreateDateColumn, Entity, JoinColumn, ManyToOne, PrimaryGeneratedColumn } from 'typeorm';
import { User } from './user.entity';

@Entity('notifications')
export class Notification {
  @PrimaryGeneratedColumn() id: number;
  @Column({ nullable: true }) user_id: number;
  @Column() type: string;
  @Column() title: string;
  @Column('text') message: string;
  @Column({ default: false }) is_read: boolean;
  @CreateDateColumn() created_at: Date;
  @ManyToOne(() => User, (u) => u.notifications, { nullable: true })
  @JoinColumn({ name: 'user_id' })
  user: User;
}
