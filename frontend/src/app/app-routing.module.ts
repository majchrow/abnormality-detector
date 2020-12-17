import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {HomeComponent} from './components/home/home.component';
import {LogsComponent} from './components/logs/logs.component';
import {MeetingsComponent} from './components/meetings/meetings.component';
import {SettingsComponent} from './components/settings/settings.component';


const routes: Routes = [
  {path: 'home', component: HomeComponent},
  // {path: 'logs', component: LogsComponent},
  {path: 'meetings', component: MeetingsComponent},
  // {path: 'settings', component: SettingsComponent},
  {path: '', redirectTo: '/home', pathMatch: 'full'},
  {path: '**', redirectTo: '/home'},
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {
}
