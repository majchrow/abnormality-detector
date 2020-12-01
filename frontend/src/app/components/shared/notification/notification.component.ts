import {Component, OnInit} from '@angular/core';
import {MeetingSSEService} from '../../../services/meeting-sse.service';
import {NotificationService} from '../../../services/notification.service';
import {MatDialog} from '@angular/material/dialog';
import {NotificationDialogComponent} from './notification-dialog/notification-dialog.component';
import {NotificationSpec} from './class/notification-struct';

@Component({
  selector: 'app-notification',
  templateUrl: './notification.component.html',
  styleUrls: ['./notification.component.scss']
})
export class NotificationComponent implements OnInit {

  constructor(
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService,
    private dialog: MatDialog
  ) {
  }


  notifications: NotificationSpec[] = [];
  count = 0;

  ngOnInit(): void {
    this.subscribeSSEs();
  }

  subscribeSSEs() {
    this.meetingSSEService.getServerSentEvents().subscribe(
      next => {
        const tmpData = JSON.parse(next.data);
        const name = tmpData.name;
        const data = tmpData.event;
        this.notifications.push(
          new NotificationSpec(
            'info',
            `${name}`,
            `${data}`
          )
        );
        this.count += 1;
      },
      error => {
        this.notificationService.warn(error.data);
      }
    );
  }


  onClick() {
    if (this.count !== 0) {
      this.count = 0;
      this.openDialog();
    }
  }

  openDialog(): void {
    const dialog = this.dialog.open(NotificationDialogComponent, {
      panelClass: 'app-full-bleed-dialog',
      data: this.notifications,
      position: {top: '40px', right: '50px'}
    });

    dialog.afterClosed().subscribe(
      () => this.notifications = []
    );
  }

}
