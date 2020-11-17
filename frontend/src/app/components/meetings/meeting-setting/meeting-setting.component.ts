import {Component, Input, OnInit} from '@angular/core';
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
    private notificationService: NotificationService,
  ) {
  }

  @Input() meeting: Meeting;


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
          max_hour: 0
        },
      },
      day1: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 0
        },
      },
      day2: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 0
        },
      },
      day3: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 0
        },
      },
      day4: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 0
        },
      },
      day5: {
        checked: false,
        conditions: {
          min_hour: 0,
          max_hour: 0
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
          max_hour: 0
        },
      }
    };
  }

  ngOnInit(): void {
    this.fetchConfig();
    this.config = this.getDefaultConfig();
    console.log(this.config);
  }

  getDefaultConfig(): Record<string, any> {
    return {
      time_diff: {
        checked: false,
        conditions: {
          min: 0,
          max: 0
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

  fetchConfig() {
    this.meetingsService.fetch_criteria('Spotkanie').subscribe(
      next => console.log(next.criteria),
      err => console.log(err)
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
        console.log(this.config);
      }
    );
  }

  save() {
    this.dialogService.openConfirmDialog('Are you sure you want to save changes?')
      .afterClosed().subscribe(res => {
        console.log(this.preparePost());
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


  preparePost() {
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
    console.log(result);
    return result;

  }


  sliderOptions(): Options {
    return {
      floor: 0,
      ceil: 600,
      showTicks: false,
      disabled: !this.config.time_diff.checked,
      translate: (value: number, label: LabelType): string => {
        return `<b>${this.translate(value)}</b>`;
      }
    };
  }
}
