import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {MeetingsService} from '../../../services/meetings.service';
import {NotificationService} from '../../../services/notification.service';
import {MeetingSSEService} from '../../../services/meeting-sse.service';

@Component({
  selector: 'app-meeting-model',
  templateUrl: './meeting-model.component.html',
  styleUrls: ['./meeting-model.component.scss']
})
export class MeetingModelComponent implements OnInit {


  options = {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };

  @Input() meeting: Meeting;
  @Output() exitClick = new EventEmitter<any>();

  date = {begin: new Date(), end: new Date()};
  participants = 0;
  duration = 0;
  threshold = 90;
  last: string;


  constructor(
    private dialogService: ConfirmationDialogService,
    private meetingsService: MeetingsService,
    private meetingSSEService: MeetingSSEService,
    private notificationService: NotificationService
  ) {
  }

  ngOnInit(): void {
    this.getLast();
  }

  getLast() {
    this.meetingsService.getModelInfo(this.meeting).subscribe(
      res => {
        console.log(res.last);
        if (res.last) {
          this.last = new Date(Date.parse(res.last)).toLocaleString('en-GB', this.options);
        } else {
          this.last = 'Not trained';
        }
      }, err => {
        console.log(err);
      }
    );
  }

  onExitClick(): void {
    this.exitClick.emit();
  }

  restoreDefault() {
    this.date = {begin: new Date(), end: new Date()};
    this.participants = 0;
    this.duration = 0;

  }

  saveDate(event: any) {
    this.date = event.target.value;
  }


  formatPercent(value: number | null): string {
    if (!value) {
      return '0%';
    }
    return `${value}%`;
  }

  formatLabel(value: number | null): string {
    if (!value) {
      return '00:00';
    }

    let hour = `${Math.floor(value / 60)}`;
    let min = `${value % 60}`;

    if (hour.length !== 2) {
      hour = '0' + hour;
    }

    if (min.length !== 2) {
      min = '0' + min;
    }
    return `${hour}:${min}`;
  }

  restore() {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(() => {
        this.restoreDefault();
      }
    );
  }

  save() {
    // tslint:disable-next-line:max-line-length
    this.meetingsService.fetchMeetingHistoryModel(this.meeting.name, this.date.begin, this.date.end, this.participants, this.duration * 60).subscribe(
      res => {
        const calls = res.calls.map(el => new Date(Date.parse(el.start)).toISOString());
        if (calls.length === 0) {
          this.notificationService.warn('No meetings found for given range and criteria');
        } else {
          this.meetingSSEService.trainModel(this.meeting, calls, this.threshold).subscribe(
            () => {
              this.notificationService.success(`Model scheduled to train on ${calls.length} meetings`);
            },
            error => {
              console.log(error);
              this.notificationService.warn(error.message);
            }
          );
        }
      },
      err => {
        console.log(err);
      });
  }

}
