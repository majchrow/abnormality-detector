import {BrowserModule} from '@angular/platform-browser';
import {NgModule} from '@angular/core';

import {AppRoutingModule} from './app-routing.module';
import {AppComponent} from './app.component';
import {HeaderComponent} from './components/header/header.component';
import {HomeComponent} from './components/home/home.component';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatCardModule} from '@angular/material/card';
import {MeetingsComponent} from './components/meetings/meetings.component';
import {LogsComponent} from './components/logs/logs.component';
import {SettingsComponent} from './components/settings/settings.component';
import {FlexLayoutModule} from '@angular/flex-layout';
import {MatPaginatorModule} from '@angular/material/paginator';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {MeetingCardComponent} from './components/meetings/meeting-card/meeting-card.component';
import {MatListModule} from '@angular/material/list';
import {MatConfirmDialogComponent} from './components/mat-confirm-dialog/mat-confirm-dialog.component';
import {MatDialogModule} from '@angular/material/dialog';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import { LogComponent } from './components/logs/log/log.component';
import { PlotComponent } from './components/logs/plot/plot.component';
import { FirstCardComponent } from './components/home/first-card/first-card.component';
import { SecondCardComponent } from './components/home/second-card/second-card.component';
import { ThirdCardComponent } from './components/home/third-card/third-card.component';
import { MeetingSettingComponent } from './components/meetings/meeting-setting/meeting-setting.component';
import {MatFormFieldModule} from "@angular/material/form-field";
import {MatInputModule} from "@angular/material/input";

@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    HomeComponent,
    MeetingsComponent,
    LogsComponent,
    SettingsComponent,
    MeetingCardComponent,
    MatConfirmDialogComponent,
    LogComponent,
    PlotComponent,
    FirstCardComponent,
    SecondCardComponent,
    ThirdCardComponent,
    MeetingSettingComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatButtonToggleModule,
    MatCardModule,
    FlexLayoutModule,
    MatPaginatorModule,
    BrowserAnimationsModule,
    MatListModule,
    MatDialogModule,
    MatSnackBarModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatInputModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {
}
