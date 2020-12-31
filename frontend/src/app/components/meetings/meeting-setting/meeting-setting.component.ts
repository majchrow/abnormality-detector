import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {NotificationService} from '../../../services/notification.service';
import {LabelType, Options} from '@angular-slider/ngx-slider';
import {DaysDialogComponent} from './days-dialog/days-dialog.component';
import {MeetingsService} from '../../../services/meetings.service';

@Component({
  selector: 'app-meeting-setting',
  templateUrl: './meeting-setting.component.html',
  styleUrls: ['./meeting-setting.component.scss']
})
export class MeetingSettingComponent implements OnInit {

  constructor(
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
    private meetingsService: MeetingsService,
    private notificationService: NotificationService
  ) {
  }

  @Input() meeting: Meeting;
  @Output() exitClick = new EventEmitter<any>();
  @Output() successClick = new EventEmitter<any>();

  config: Record<string, any>;

  public static translateDay(key: string) {
    return {
      day0: 'Monday',
      day1: 'Tuesdays',
      day2: 'Wednesday',
      day3: 'Thursday',
      day4: 'Friday',
      day5: 'Saturday',
      day6: 'Sunday'
    }[key];
  }

  public static getDefaultDaysConfig(): Record<string, any> {
    return {
      day0: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      },
      day1: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      },
      day2: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      },
      day3: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      },
      day4: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      },
      day5: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      },
      day6: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 0
        },
      },
      day7: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 1
        },
      }
    };
  }

  ngOnInit(): void {
    this.fetchConfig(this.meeting);
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

  fetchConfig(meeting: Meeting) {
    this.meetingsService.fetchMeetings().subscribe(
      meetings => {
        if (meetings.created.map(met => met.name).includes(this.meeting.name)) {
          this.meetingsService.fetchMeeting(meeting.name).subscribe(
            next => {
              this.config = this.parsePayload(next.criteria);
            },
            err => {
              if (err.status !== 404) {
                console.log(err);
              }
              this.config = this.getDefaultConfig();
            }
          );
        } else {
          this.config = this.getDefaultConfig();
        }

      },
      err => {
        console.log(err);
        this.config = this.getDefaultConfig();
      }
    );
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

  restore() {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(res => {
        this.config = this.getDefaultConfig();
      }
    );
  }

  save() {
    this.dialogService.openConfirmDialog('Are you sure you want to save changes?')
      .afterClosed().subscribe(res => {
        this.meetingsService.putMeeting(new Meeting(
          this.meeting.name,
          this.meeting.meeting_number,
          this.preparePayload()
        )).subscribe(
          () => {
            setTimeout(() => {
              this.notificationService.success('Updates successfully');
              this.successClick.emit(this.meeting);
            }, 1000);
          },
          () => {
            this.notificationService.warn('Update failed');
          }
        );
      }
    );
  }

  onSliderChange(key: any) {
    key.conditions = !key.conditions;
  }

  onChange(key: any) {
    key.checked = !key.checked;
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

  revertDays(key: number): number {
    return {
      1: 'day0',
      2: 'day1',
      3: 'day2',
      4: 'day3',
      5: 'day4',
      6: 'day5',
      7: 'day6'
    }[key];
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


  revertTranslate(date: string) {
    const tmp = date.split(':');
    const hour: number = +tmp[0];
    const min: number = +tmp[1];
    return hour * 60 + min;
  }

  translateCondition(condition: any): any {
    return {
      min_hour: this.translate(condition.min_hour),
      max_hour: this.translate(condition.max_hour)
    };
  }

  parsePayload(data: Array<any>) {
    const config = this.getDefaultConfig();
    for (const record of data) {
      console.log(record);
      if (record.parameter === 'days') {
        const daysConfig = MeetingSettingComponent.getDefaultDaysConfig();
        for (const day of record.conditions) {
          const dayKey = this.revertDays(day.day);
          daysConfig[dayKey].conditions = {
            min_hour: this.revertTranslate(day.min_hour),
            max_hour: this.revertTranslate(day.max_hour)
          };
          daysConfig[dayKey].checked = true;
        }
        config[record.parameter].conditions = daysConfig;
      } else if (record.parameter === 'active_speaker') {
        config[record.parameter].conditions = record.conditions.max;
      } else if (record.parameter === 'current_participants') {
        config.max_participants.conditions = record.conditions.max;
      } else {
        config[record.parameter].conditions = record.conditions;
      }
      if (record.parameter === 'current_participants') {
        config.max_participants.checked = true;
      } else {
        config[record.parameter].checked = true;
      }
    }

    return config;
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
        } else if (key === 'max_participants') {
          result.push(
            {
              parameter: 'current_participants',
              conditions: {max: value.conditions}
            }
          );
        } else if (key === 'active_speaker') {
          result.push(
            {
              parameter: key,
              conditions: {max: value.conditions}
            }
          );
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

  onExitClick(): void {
    this.exitClick.emit();
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
}
