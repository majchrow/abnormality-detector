import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';
import {MeetingSSEService} from '../../../../services/meeting-sse.service';
import {NotificationService} from '../../../../services/notification.service';
import {Observable} from 'rxjs';

@Component({
  selector: 'app-meeting-card-current',
  templateUrl: './meeting-card-current.component.html',
  styleUrls: ['./meeting-card-current.component.scss']
})
export class MeetingCardCurrentComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() historyEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();

  monitoring: Observable<any>;
  monitored = false;

  constructor(
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService
  ) {
  }

  ngOnInit(): void {
    this.fetchMonitoring();
  }

  fetchMonitoring() {
    this.meetingSSEService.fetchMonitoring(this.meeting.name).subscribe(
      res => {
        this.monitored =  res.monitored;
      }, err => {
        console.log(err.status);
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

  onSettingClick() {
    this.settingEmitter.emit(this.meeting);
  }

  onHistoryClick() {
    this.historyEmitter.emit(this.meeting);
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
