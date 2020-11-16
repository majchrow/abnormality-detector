import {Component, Input, OnInit} from '@angular/core';
import {Meeting} from '../class/meeting';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {NotificationService} from '../../../services/notification.service';
import {Options} from '@angular-slider/ngx-slider';

@Component({
  selector: 'app-meeting-setting',
  templateUrl: './meeting-setting.component.html',
  styleUrls: ['./meeting-setting.component.scss']
})
export class MeetingSettingComponent implements OnInit {

  @Input() meeting: Meeting;

  constructor(
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
    private notificationService: NotificationService
  ) {
  }

  config: Record<string, any> = {
    time_diff: {checked: true}

  };
  value = 0;
  highValue = 0;

  ngOnInit(): void {
  }


  save() {
    this.dialogService.openConfirmDialog('Are you sure you want to save changes?')
      .afterClosed().subscribe(res => {
        console.log(res);
      }
    );
  }

  test() {
    console.log(this.config.time_diff.checked);
  }

  onChange(key: any) {
    key.checked = !key.checked;
  }

  sliderOptions(): Options {
    return {
      floor: 0,
      ceil: 300,
      step: 5,
      showTicks: false,
      disabled: !this.config.time_diff.checked
    };
  }
}
