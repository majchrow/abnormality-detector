import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {LabelType, Options} from '@angular-slider/ngx-slider';
import {MeetingSettingComponent} from '../meeting-setting.component';
import {ConfirmationDialogService} from '../../../../services/confirmation-dialog.service';

@Component({
  selector: 'app-days-dialog',
  templateUrl: './days-dialog.component.html',
  styleUrls: ['./days-dialog.component.scss']
})
export class DaysDialogComponent implements OnInit {


  constructor(
    private dialogService: ConfirmationDialogService,
    public dialogRef: MatDialogRef<DaysDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
  }

  dataCopy: any;


  ngOnInit(): void {
    this.dataCopy = this.deepCopy(this.data);
  }


  onExitClick(): void {
    this.dialogRef.close(this.dataCopy);
  }

  onRestoreClick(): void {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(res => {
        this.data = MeetingSettingComponent.getDefaultDaysConfig();
      }
    );
  }

  onSaveClick(): void {
    this.dialogRef.close(this.data);
  }

  onChange(key: any) {
    key.checked = !key.checked;
  }


  sliderOptions(key: string): Options {
    return {
      floor: 0,
      showTicks: false,
      ceil: 1439,
      disabled: !this.data[key].checked,
      translate: (value: number, label: LabelType): string => {
        let hour = `${Math.floor(value / 60)}`;
        let min = `${value % 60}`;

        if (hour.length !== 2) {
          hour = '0' + hour;
        }

        if (min.length !== 2) {
          min = '0' + min;
        }
        return `<b>${hour}:${min}</b>`;
      }
    };
  }

  translateDay(key: string) {
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


  deepCopy(obj) {
    let copy;

    // Handle the 3 simple types, and null or undefined
    if (null == obj || 'object' !== typeof obj) {
      return obj;
    }

    // Handle Date
    if (obj instanceof Date) {
      copy = new Date();
      copy.setTime(obj.getTime());
      return copy;
    }

    // Handle Array
    if (obj instanceof Array) {
      copy = [];
      for (let i = 0, len = obj.length; i < len; i++) {
        copy[i] = this.deepCopy(obj[i]);
      }
      return copy;
    }

    // Handle Object
    if (obj instanceof Object) {
      copy = {};
      for (const attr in obj) {
        if (obj.hasOwnProperty(attr)) {
          copy[attr] = this.deepCopy(obj[attr]);
        }
      }
      return copy;
    }

    throw new Error('Unable to copy obj! Its type isn\'t supported.');
  }
}
