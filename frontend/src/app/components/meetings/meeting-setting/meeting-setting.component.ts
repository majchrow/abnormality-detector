import {Component, Input, OnInit} from '@angular/core';
import {Meeting} from '../class/meeting';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {NotificationService} from '../../../services/notification.service';

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

  config: Map<string, any>;

  ngOnInit(): void {
    this.config = new Map(this.meeting.config);
  }


  save() {
    this.dialogService.openConfirmDialog('Are you sure you want to save changes?')
      .afterClosed().subscribe(res => {
        if (res) {
          this.meeting.config = new Map(this.config);
          this.notificationService.success('Saved successfully');
          console.log(this.meeting);
        }
      }
    );
  }

  onChange(key: string) {
    this.config.set(key, !this.config.get(key));
  }
}
