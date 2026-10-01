import type { Meta, StoryObj } from '@storybook/vue3';
import ReviewItem from './ReviewItem.vue';
import { setTaskProgressFixture } from '../../storybook/daemon.fixture';
import type { ReportedTask } from './types';
const meta = {title:'Dashboard/ReviewItem',component:ReviewItem,args:{agent:'thread-1',task:exampleTask(),threadLabel:'Bug fixing',offline:false},render:args=>{
 setTaskProgressFixture({threads:{'thread-1':{'review-1':JSON.parse(JSON.stringify(args.task))}},error:null});
 return {components:{ReviewItem},setup:()=>({args}),template:'<div style="width:260px;padding:16px"><ReviewItem v-bind="args" /></div>'};
}} satisfies Meta<typeof ReviewItem>;
export default meta;
type Story = StoryObj<typeof meta>;
export const DirectLink: Story = {};
export const Opened: Story = {args:{task:{...exampleTask(),review_state:'opened'}}};
export const Wrapper: Story = {args:{task:{...exampleTask(),report:{...exampleTask().report,review:{label:'Review preview',url:'http://localhost:6041',direct:false}}}}};

function exampleTask(): ReportedTask {
return {report:{task_id:'review-1',revision:1,title:'New onboarding flow',state:'done',completed:3,total:3,participant:null,role:null,model:null,review:{label:'Review onboarding',url:'https://gitlab.com/gitlab-org/gitlab',direct:true}},review_state:'unopened',updated_at:Date.now()/1000,stale:false};
}
