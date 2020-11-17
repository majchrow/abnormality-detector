import {Component, OnInit} from '@angular/core';
import {MatDialogRef} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {MeetingsService} from '../../../services/meetings.service';
import {Meeting} from '../class/meeting';
import {NotificationService} from '../../../services/notification.service';

@Component({
  selector: 'app-new-meeting-dialog',
  templateUrl: './new-meeting-dialog.component.html',
  styleUrls: ['./new-meeting-dialog.component.scss']
})
export class NewMeetingDialogComponent implements OnInit {

  constructor(
    private dialogService: ConfirmationDialogService,
    private notificationService: NotificationService,
    public dialogRef: MatDialogRef<NewMeetingDialogComponent>,
    private meetingsService: MeetingsService
  ) {
  }

  name = '';

  ngOnInit(): void {
  }

  onExitClick(): void {
    this.dialogRef.close(this.name);
  }

  onRestoreClick(): void {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(res => {
        this.name = '';
      }
    );
  }

  onSaveClick(): void {
    this.dialogService.openConfirmDialog('Are you sure you want to create this meeting?')
      .afterClosed().subscribe(res => {
        this.meetingsService.put_meeting(
          new Meeting(this.name, [])
        ).subscribe(
          result => {
            this.notificationService.success(
              'Meeting added sucessfully'
            );
            this.dialogRef.close(this.name);
          }, err => {
            this.notificationService.warn(
              'Failed to add meeting'
            );
            this.dialogRef.close(this.name);
          }
        );
      }
    );
  }
}