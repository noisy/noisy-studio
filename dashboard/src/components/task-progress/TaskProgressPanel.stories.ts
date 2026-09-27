import type {Meta,StoryObj} from '@storybook/vue3';
import App from '../../App.vue';
import {resetScenario,setTaskProgressFixture} from '../../storybook/daemon.fixture';
import type {ReportedTask} from './types';
function task(id:string,title:string,state:'working'|'done',review=false):ReportedTask{return{report:{task_id:id,revision:1,title,state,completed:state==='done'?3:1,total:3,participant:'child-'+id,role:'Dashboard agent',model:'GPT-6 Sol',review:review?{label:'Review Stage preview',url:new URL('/iframe.html?id=lab-stage-crew--just-faces&viewMode=story',window.location.href).href}:null},started_at:Date.now()/1000-167,updated_at:Date.now()/1000,review_state:'unopened',stale:false};}
const meta={title:'Dashboard/TaskProgressPanel',component:App,parameters:{layout:'fullscreen'},render:()=>{resetScenario('conversation',{agent_labels:{codex:'Bug fixing',claude:'Bucky',docs:'QA'}});setTaskProgressFixture({threads:{codex:{'task-1':task('task-1','Task review layout','done',true),'task-2':task('task-2','Audio handover','working')},claude:{'task-3':task('task-3','TestFlight build 430','working')}},error:null});return{components:{App},template:'<App />'};}} satisfies Meta<typeof App>;
export default meta;
type Story=StoryObj<typeof meta>;
export const ConnectedReview:Story={};
