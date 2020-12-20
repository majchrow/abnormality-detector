import {Component, OnInit} from '@angular/core';
import {MeetingSSEService} from '../../../services/meeting-sse.service';
import {NotificationService} from '../../../services/notification.service';
import {MatDialog} from '@angular/material/dialog';
import {NotificationDialogComponent} from './notification-dialog/notification-dialog.component';
import {NotificationSpec} from './class/notification-struct';
import {MeetingsService} from '../../../services/meetings.service';

@Component({
  selector: 'app-notification',
  templateUrl: './notification.component.html',
  styleUrls: ['./notification.component.scss']
})
export class NotificationComponent implements OnInit {

  constructor(
    private meetingsService: MeetingsService,
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService,
    private dialog: MatDialog
  ) {
  }


  dates: string[] = [];
  count = 0;

  ngOnInit(): void {
    this.subscribeSSEs();
  }

  fetchNotifications() {
    this.meetingsService.fetchNotifications(15).subscribe(
      res => {
        let data: NotificationSpec[] = res.last.map(
          el => new NotificationSpec(
            el.status,
            el.name,
            el.event,
            new Date(Date.parse(el.timestamp)),
            this.dates.indexOf(new Date(Date.parse(el.timestamp)).toISOString()) > -1
          ));
        data = data.reverse();
        this.count = 0;
        this.dates = [];
        this.openDialog(data);
      }, err => {
        console.log(err);
      }
    );
  }

  subscribeSSEs() {
    this.meetingSSEService.getServerSentEvents().subscribe(
      next => {
        const tmpData = JSON.parse(next.data);
        this.dates.push(new Date(Date.parse(tmpData.timestamp)).toISOString());
        this.count += 1;
      },
      error => {
        console.log(error);
        setTimeout(() => this.subscribeSSEs(), 3000);
      }
    );
  }


  onClick() {
    this.fetchNotifications();
  }

  openDialog(data): void {
    const dialog = this.dialog.open(NotificationDialogComponent, {
      panelClass: 'app-full-bleed-dialog',
      data,
      position: {top: '40px', right: '50px'}
    });

    dialog.afterClosed().subscribe(
      () => {
      }
    );
  }

}
