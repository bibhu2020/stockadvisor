import { Column, CreateDateColumn, Entity, OneToMany, PrimaryGeneratedColumn } from 'typeorm';
import { Notification } from './notification.entity';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn() id: number;
  @Column({ unique: true }) email: string;
  @Column() name: string;
  @Column() password_hash: string;
  @Column({ default: 'pending' }) role: string; // admin | guest | pending
  @Column({ nullable: true }) approved_at: Date;
  @CreateDateColumn() created_at: Date;
  @OneToMany(() => Notification, (n) => n.user) notifications: Notification[];
}
