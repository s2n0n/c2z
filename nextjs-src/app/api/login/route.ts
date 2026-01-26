import { NextResponse } from 'next/server';
import { z } from 'zod';

const loginSchema = z.object({
  username: z.string(),
  password: z.string(),
});

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { username, password } = loginSchema.parse(body);

    let role = '';

    if (username === 'admin' && password === 'admin') {
      role = 'admin';
    } else if (username === 'guest' && password === 'guest') {
      role = 'guest';
    } else {
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
    }

    const response = NextResponse.json({ success: true, role });
    response.cookies.set('user_role', role, { 
      httpOnly: true, 
      path: '/' 
    });
    
    return response;

  } catch (e) {
    return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
  }
}
