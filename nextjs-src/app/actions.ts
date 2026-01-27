'use server'

import { z } from 'zod';
import { revalidatePath } from 'next/cache';

const CommentSchema = z.object({
  comment: z.string().min(1, { message: "내용을 입력해주세요." }).max(100, { message: "100자를 넘을 수 없습니다." }),
});

export async function saveComment(formData: FormData) {
  const result = CommentSchema.safeParse({
    comment: formData.get('comment'),
  });

  if (!result.success) {
    console.error("Validation Failed:", result.error.flatten());
    return { success: false, error: "잘못된 입력값입니다." };
  }

  const cleanData = result.data.comment;
  console.log("Verified Data Received:", cleanData);
  
  /* await prisma.comment.create({ data: { content: cleanData } }); */

  revalidatePath('/');
  return { success: true };
}
