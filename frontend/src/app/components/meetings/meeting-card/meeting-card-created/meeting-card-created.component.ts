import {Component, EventEmitter, Input, OnDestroy, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';
import {MeetingSSEService} from '../../../../services/meeting-sse.service';
import {NotificationService} from '../../../../services/notification.service';
import {Observable, Subscription} from 'rxjs';

@Component({
  selector: 'app-meeting-card-created',
  templateUrl: './meeting-card-created.component.html',
  styleUrls: ['./meeting-card-created.component.scss']
})
export class MeetingCardCreatedComponent implements OnInit, OnDestroy {

  @Input() meeting: Meeting;
  @Output() deleteEmitter = new EventEmitter<Meeting>();
  @Output() historyEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();

  constructor(
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService
  ) {
  }

  monitoring: Observable<any>;
  subscription: Subscription;
  monitored = false;
  count = 0;


  ngOnInit(): void {
    this.fetchMonitoring();
  }

  ngOnDestroy(): void {
    this.unsubscribeMonitoring();
  }

  fetchMonitoring() {
    this.meetingSSEService.fetchMonitoring(this.meeting.name).subscribe(
      res => {
        this.monitored = res.monitored;
        if (this.monitored) {
          this.subscribeMonitoring();
        }
      }, err => {
        console.log(err);
      }
    );
  }


  subscribeMonitoring() {
    this.monitoring = this.meetingSSEService.getServerSentEvent(this.meeting.name);
    this.subscription = this.monitoring.subscribe(
      res => {
        this.count += 1;
        console.log(res);
      },
      error => {
        console.log(error);
        if (error.eventPhase !== 2) {
          this.notificationService.warn(error.message);
        }
      });
  }

  unsubscribeMonitoring() {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
    this.monitoring = null;
  }

  onSettingClick() {
    this.settingEmitter.emit(this.meeting);
  }

  onHistoryClick() {
    this.historyEmitter.emit(this.meeting);
  }

  onDeleteClick() {
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
      this.unsubscribeMonitoring();
      this.meetingSSEService.deleteMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('Deletes monitoring successfully');
          this.monitored = false;
        },
        () => {
          this.notificationService.warn('Delete monitoring failed');
        }
      );
    }
  }

}
