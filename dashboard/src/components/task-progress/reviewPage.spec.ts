import { expect, it } from 'vitest';
import { reviewPageUrl, reviewPageTarget } from './reviewPage';
it('links to the same daemon dashboard prefix and encodes the task identity', () => {
 const url=reviewPageUrl('thread/1','task & 2',3,'http://localhost:7765/next/?old=1#previous');
 expect(url).toBe('http://localhost:7765/next/?review_agent=thread%2F1&review_task=task+%26+2&review_revision=3');
 expect(reviewPageTarget(new URL(url).search)).toEqual({agent:'thread/1',taskId:'task & 2',revision:3});
 expect(reviewPageTarget('')).toBeNull();
});
