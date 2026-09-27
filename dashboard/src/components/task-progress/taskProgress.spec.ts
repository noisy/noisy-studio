import {describe,expect,it} from 'vitest';
import {readyForReview,reviewUrl,type ReportedTask} from './types';
const task:ReportedTask={report:{task_id:'task-1',revision:1,title:'Preview settings',state:'done',completed:3,total:3,participant:null,role:null,model:null,review:{label:'Preview',url:'http://localhost:6038/preview'}},updated_at:100,review_state:'unopened',stale:false};
describe('human review state',()=>{
 it('keeps opened results awaiting review until approved',()=>{expect([readyForReview(task),readyForReview({...task,review_state:'opened'}),readyForReview({...task,review_state:'approved'})]).toEqual([true,true,false]);});
 it('does not offer review for incomplete or unsafe artifacts',()=>{expect([readyForReview({...task,report:{...task.report,state:'working'}}),reviewUrl({...task,report:{...task.report,review:{label:'Bad',url:'javascript:alert(1)'}}})]).toEqual([false,null]);});
});
