import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {NotificationService} from '../../../services/notification.service';
import {MeetingsService} from '../../../services/meetings.service';
import {HistoryMeeting} from '../meeting-history/class/history-meeting';
import {FormControl, Validators} from '@angular/forms';
import {MeetingSettingComponent} from '../meeting-setting/meeting-setting.component';
import {LabelType, Options} from '@angular-slider/ngx-slider';
import {DaysDialogComponent} from '../meeting-setting/days-dialog/days-dialog.component';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {MeetingSSEService} from '../../../services/meeting-sse.service';

@Component({
  selector: 'app-meeting-inference',
  templateUrl: './meeting-inference.component.html',
  styleUrls: ['./meeting-inference.component.scss']
})
export class MeetingInferenceComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() exitClick = new EventEmitter<any>();
  @Output() successClick = new EventEmitter<Meeting>();

  constructor(
    private notificationService: NotificationService,
    private meetingsService: MeetingsService,
    private meetingSSEService: MeetingSSEService,
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
  ) {
  }


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

  date = {begin: new Date(), end: new Date()};
  participants = 0;
  duration = 0;
  threshold = 95;
  last: string;
  meetingsHistory: HistoryMeeting[];
  filterModels = ['ml model', 'admin model'];
  selectedModel = '';
  selectedMeeting = '';
  trueSelectedMeeting: HistoryMeeting;
  meetingControl = new FormControl('', Validators.required);
  modelControl = new FormControl('', Validators.required);
  config: Record<string, any> = this.getDefaultConfig();

  ngOnInit(): void {
    this.fetchHistoryMeeting();
  }


  onSelectMeetingChange() {
    this.trueSelectedMeeting = this.meetingsHistory.find(el => el.start.toISOString() === this.selectedMeeting);
  }

  onSelectModelChange() {
  }

  fetchHistoryMeeting() {
    this.meetingsService.fetchMeetingHistory(this.meeting.name).subscribe(
      res => {
        this.meetingsHistory = res.calls.map(el => new HistoryMeeting(new Date(Date.parse(el.start)), new Date(Date.parse(el.end))));
      }, err => {
        console.log(err);
      }
    );
  }

  restoreModelDefault() {
    this.date = {begin: new Date(), end: new Date()};
    this.participants = 0;
    this.duration = 0;
  }

  restoreAdminDefault() {
    this.config = this.getDefaultConfig();
  }

  onRestoreClick() {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(() => {
        if (this.selectedModel === 'ml model') {
          this.restoreModelDefault();
        } else {
          this.restoreAdminDefault();
        }
      }
    );
  }


  onExitClick(): void {
    this.exitClick.emit();
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


  onSliderChange(key: any) {
    key.conditions = !key.conditions;
  }

  onChange(key: any) {
    key.checked = !key.checked;
  }

  openDaysDialog(): void {
    const dialogRef = this.dialog.open(DaysDialogComponent, {
      disableClose: true,
      data: this.config.days.conditions
    });

    dialogRef.afterClosed().subscribe(result => {
      this.config.days.conditions = result;
    });
  }

  getDefaultConfig(): Record<string, any> {
    return {
      time_diff: {
        checked: false,
        conditions: {
          min: 0,
          max: 1
        }
      },
      recording: {
        checked: false,
        conditions: false
      },
      streaming: {
        checked: false,
        conditions: false
      },
      max_participants: {
        checked: false,
        conditions: 0
      },
      active_speaker: {
        checked: false,
        conditions: 0
      },
      days: {
        checked: false,
        conditions: MeetingSettingComponent.getDefaultDaysConfig()
      }
    };
  }

  translate(value: number) {
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

  translateCondition(condition: any): any {
    return {
      min_hour: this.translate(condition.min_hour),
      max_hour: this.translate(condition.max_hour)
    };
  }

  sliderOptions(): Options {
    return {
      floor: 0,
      ceil: 480,
      showTicks: false,
      disabled: !this.config.time_diff.checked,
      translate: (value: number, label: LabelType): string => {
        return `<b>${this.translate(value)}</b>`;
      }
    };
  }

  translateDay(key: string): number {
    return {
      day0: 1,
      day1: 2,
      day2: 3,
      day3: 4,
      day4: 5,
      day5: 6,
      day6: 7
    }[key];
  }

  preparePayload() {
    const result: Array<any> = [];

    for (const [key, value] of Object.entries(this.config)) {
      if (value.checked) {
        if (key === 'days') {
          const days: Array<any> = [];
          for (const [day, dayValue] of Object.entries(value.conditions)) {
            // @ts-ignore
            if (dayValue.checked) {
              const correctDay = this.translateDay(day);
              // @ts-ignore
              const dayInfo = this.translateCondition(dayValue.conditions);
              dayInfo.day = correctDay;
              days.push(dayInfo);
            }
          }
          result.push(
            {
              parameter: 'days',
              conditions: days
            });
        } else {
          result.push(
            {
              parameter: key,
              conditions: value.conditions
            }
          );
        }

      }
    }
    return result;

  }

  onEvaluateClick() {
    if (!this.trueSelectedMeeting) {
      console.log('FAILED - selected meeting');
    } else if (this.selectedModel === 'ml model') {
      this.evaluateModel();
    } else {
      this.evaluateAdmin();
    }
  }

  evaluateModel() {
    // tslint:disable-next-line:max-line-length
    this.meetingsService.fetchMeetingHistoryModel(this.meeting.name, this.date.begin, this.date.end, this.participants, this.duration * 60).subscribe(
      res => {
        const calls = res.calls.map(el => new Date(Date.parse(el.start)).toISOString());
        if (calls.length === 0) {
          this.notificationService.warn('No meetings found for given range and criteria');
        } else {
          this.meetingSSEService.evaluateModel(this.meeting, calls, this.threshold, this.trueSelectedMeeting).subscribe(
            () => {
              this.notificationService.success(`ML model evaluation scheduled successfully. Model will be trained on ${calls.length} meetings`);
              this.successClick.emit(this.meeting);
            },
            err => {
              console.log(err);
              this.notificationService.warn('Failed to schedule evaluation');
            }
          );
        }
      },
      err => {
        console.log(err);
      });
  }

  evaluateAdmin() {
    this.meetingSSEService.evaluateAdminModel(new Meeting(
      this.meeting.name,
      this.meeting.meeting_number,
      this.preparePayload()
    ), this.trueSelectedMeeting).subscribe(
      () => {
        this.notificationService.success(`Conditions evaluation scheduled successfully.`);
        this.successClick.emit(this.meeting);
      },
      err => {
        console.log(err);
        this.notificationService.warn('Failed to schedule evaluation');
      }
    );
  }
}
