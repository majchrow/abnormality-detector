import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';
import {MeetingSSEService} from '../../../../services/meeting-sse.service';
import {NotificationService} from '../../../../services/notification.service';
import {Observable} from 'rxjs';

@Component({
  selector: 'app-meeting-card-created',
  templateUrl: './meeting-card-created.component.html',
  styleUrls: ['./meeting-card-created.component.scss']
})
export class MeetingCardCreatedComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() deleteEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();

  constructor(
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService
  ) {
  }

  monitoring: Observable<any>;
  monitored = false;

  ngOnInit(): void {
    this.fetchMonitoring();
  }

  fetchMonitoring() {
    this.meetingSSEService.fetchMonitoring(this.meeting.name).subscribe(
      res => {
        this.monitored = res.monitored;
      }, err => {
        console.log(err);
      }
    );
  }


  subscribeMonitoring() {
    this.monitoring = this.meetingSSEService.getServerSentEvent(this.meeting.name);
    this.monitoring.subscribe(
      res => console.log(res),
      err => console.log(err)
    );
  }

  unsubscribeMonitoring() {
    this.monitoring = null;
  }

  settings(event: MouseEvent) {
    this.settingEmitter.emit(this.meeting);
  }

  edit(event: MouseEvent) {
    console.log('edit');
  }

  delete(event: MouseEvent) {
    this.deleteEmitter.emit(this.meeting);
  }

  onMonitoringChange(event: boolean) {
    if (event) {
      this.meetingSSEService.putMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('Monitoring started');
          this.subscribeMonitoring();
          this.monitored = true;
        },
        () => {
          this.notificationService.warn('Starting monitoring failed');
        }
      );
    } else {
      this.meetingSSEService.deleteMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('Deletes monitoring successfully');
          this.unsubscribeMonitoring();
          this.monitored = false;
        },
        () => {
          this.notificationService.warn('Delete monitoring failed');
        }
      );
    }

  }

}
