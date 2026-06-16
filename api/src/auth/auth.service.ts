import { BadRequestException, Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { InjectRepository } from '@nestjs/typeorm';
import * as bcrypt from 'bcrypt';
import { Repository } from 'typeorm';
import { User } from '../common/entities/user.entity';

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User) private users: Repository<User>,
    private jwt: JwtService,
  ) {}

  async register(email: string, name: string, password: string) {
    const exists = await this.users.findOne({ where: { email } });
    if (exists) throw new BadRequestException('Email already registered');

    const hash = await bcrypt.hash(password, 10);
    // First user gets admin role
    const count = await this.users.count();
    const role = count === 0 ? 'admin' : 'pending';

    const user = this.users.create({ email, name, password_hash: hash, role });
    await this.users.save(user);
    return { message: role === 'admin' ? 'Admin account created' : 'Registration pending approval', role };
  }

  async login(email: string, password: string) {
    const user = await this.users.findOne({ where: { email } });
    if (!user) throw new UnauthorizedException('Invalid credentials');
    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) throw new UnauthorizedException('Invalid credentials');
    return { access_token: this._token(user), user: this._safe(user) };
  }

  async me(userId: number) {
    const user = await this.users.findOne({ where: { id: userId } });
    if (!user) throw new UnauthorizedException();
    return this._safe(user);
  }

  async updateProfile(userId: number, name: string) {
    await this.users.update(userId, { name });
    return this.me(userId);
  }

  async changePassword(userId: number, currentPassword: string, newPassword: string) {
    const user = await this.users.findOne({ where: { id: userId } });
    if (!user) throw new UnauthorizedException();
    const valid = await bcrypt.compare(currentPassword, user.password_hash);
    if (!valid) throw new BadRequestException('Current password is incorrect');
    if (newPassword.length < 8) throw new BadRequestException('New password must be at least 8 characters');
    const hash = await bcrypt.hash(newPassword, 10);
    await this.users.update(userId, { password_hash: hash });
    return { message: 'Password updated successfully' };
  }

  private _token(user: User) {
    return this.jwt.sign({ sub: user.id, email: user.email, role: user.role });
  }

  private _safe(user: User) {
    const { password_hash, ...rest } = user as User & { password_hash?: string };
    return rest;
  }
}
