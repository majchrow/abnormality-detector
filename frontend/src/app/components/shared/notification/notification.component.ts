import {Component, OnInit} from '@angular/core';
import {MeetingSSEService} from '../../../services/meeting-sse.service';
import {NotificationService} from '../../../services/notification.service';

@Component({
  selector: 'app-notification',
  templateUrl: './notification.component.html',
  styleUrls: ['./notification.component.scss']
})
export class NotificationComponent implements OnInit {

  constructor(
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService
  ) {
  }


  notifications: Array<string> = new Array<string>();
  count = 0;

  ngOnInit(): void {
    this.subscribeSSEs();
  }

  subscribeSSEs() {
    this.meetingSSEService.getServerSentEvents().subscribe(
      next => {
        this.count += 1;
        console.log(this.count);
        this.notifications.push(next.message);
      },
      error => {
        this.notificationService.warn(error.message);
      }
    );
  }


  onClick() {
    this.count = 0;
  }

}
