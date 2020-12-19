import {Component, EventEmitter, Input, OnDestroy, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';
import {MeetingSSEService} from '../../../../services/meeting-sse.service';
import {NotificationService} from '../../../../services/notification.service';
import {Observable, Subscription} from 'rxjs';
import {MeetingsService} from '../../../../services/meetings.service';

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
  @Output() modelEmitter = new EventEmitter<Meeting>();

  constructor(
    private meetingSSEService: MeetingSSEService,
    private meetingsService: MeetingsService,
    private notificationService: NotificationService
  ) {
  }

  monitoring: Observable<any>;
  subscription: Subscription;
  monitored;
  mlMonitored;
  last: boolean;
  count = 0;


  ngOnInit(): void {
    this.fetchMonitoring();
    this.fetchMl();
  }

  ngOnDestroy(): void {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  fetchMl() {
    this.meetingsService.getModelInfo(this.meeting).subscribe(
      res => {
        console.log(res);
        this.last = !!res.last;
        if (this.last) {
          this.meetingSSEService.getMLMonitoring(this.meetingsService).subscribe(
            () => {
              this.mlMonitored = true;
            },
            err => {
              this.mlMonitored = false;
            }
          );

          } else {
          this.mlMonitored = false;
        }
      }, err => {
        console.log(err);
      }
    );
  }

  fetchMonitoring() {
    this.meetingSSEService.fetchMonitoring(this.meeting.name).subscribe(
      res => {
        console.log(res);
        this.monitored = !!res.monitored;
        if (this.monitored) {
          this.subscribeMonitoring();
        }
      }, err => {
        this.monitored = false;
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

  onModelClick() {
    this.modelEmitter.emit(this.meeting);
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

  onMLMonitoringChange(event: boolean) {
    if (event) {
      this.meetingSSEService.putMLMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('ML model monitoring started');
          this.mlMonitored = true;
        },
        () => {
          this.notificationService.warn('Starting ml model monitoring failed');
        }
      );
    } else {
      this.unsubscribeMonitoring();
      this.meetingSSEService.deleteMLMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('Deletes ml model monitoring successfully');
          this.monitored = false;
        },
        () => {
          this.notificationService.warn('Delete ml model monitoring failed');
        }
      );
    }
  }

  onMonitoringChange(event: boolean) {
    if (event) {
      this.meetingSSEService.putMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('Admin model monitoring started');
          this.subscribeMonitoring();
          this.monitored = true;
        },
        () => {
          this.notificationService.warn('Starting admin model monitoring failed');
        }
      );
    } else {
      this.unsubscribeMonitoring();
      this.meetingSSEService.deleteMonitoring(this.meeting).subscribe(
        () => {
          this.notificationService.success('Deletes admin model monitoring successfully');
          this.monitored = false;
        },
        () => {
          this.notificationService.warn('Delete admin model monitoring failed');
        }
      );
    }
  }

}
