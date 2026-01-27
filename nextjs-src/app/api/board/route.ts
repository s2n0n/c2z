import { NextResponse } from 'next/server';
import { z } from 'zod';

let posts = [
  { id: 1, title: 'Welcome', content: 'This is the first notice.', author: 'admin' },
  { id: 2, title: 'Rule', content: 'Do not hack this server... yet.', author: 'admin' }
];

const postSchema = z.object({
  title: z.string().min(1, "Title is required"),
  content: z.string().min(1, "Content is required"),
  author: z.string(),
});

export async function GET() {
  return NextResponse.json(posts);
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    const newPost = postSchema.parse(body);
    
    const postWithId = { ...newPost, id: posts.length + 1 };
    posts.push(postWithId);
    
    return NextResponse.json({ success: true, post: postWithId });
  } catch (e) {
    return NextResponse.json({ error: 'Validation failed' }, { status: 400 });
  }
}
