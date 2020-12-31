import {Component, OnInit} from '@angular/core';
import {MatDialogRef} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';
import {MeetingsService} from '../../../services/meetings.service';
import {Meeting} from '../class/meeting';
import {NotificationService} from '../../../services/notification.service';
import {FormControl, Validators} from '@angular/forms';

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

  meetingControl = new FormControl('', Validators.required);
  meetings: string[];
  selectedName = '';

  ngOnInit(): void {
    this.fetchCurrentMeetings();
  }

  fetchCurrentMeetings() {
    this.meetingsService.fetchMeetings().subscribe(
      next => {
        this.fetchMeetings(next.created);
      },
      error => {
        console.log(error);
        this.fetchMeetings([]);
      }
    );
  }

  fetchMeetings(current: Meeting[]) {
    const names = current.map(el => el.name);
    this.meetingsService.fetchPublicMeetings().subscribe(
      next => {
        this.meetings = next.meetings.meetings.map(meeting => meeting.name).filter(el => names.indexOf(el) === -1);
      },
      error => {
        console.log(error);
      }
    );
  }

  onExitClick()
    :
    void {
    this.dialogRef.close(this.selectedName);
  }

  onRestoreClick()
    :
    void {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(res => {
        if (res) {
          this.selectedName = '';
        }
      }
    );
  }

  onSaveClick()
    :
    void {
    this.dialogService.openConfirmDialog('Are you sure you want to create this meeting?')
      .afterClosed().subscribe(res => {
        if (res) {
          this.meetingsService.putMeeting(
            new Meeting(this.selectedName, -1, [])
          ).subscribe(
            result => {
              this.notificationService.success(
                'Meeting added sucessfully'
              );
              this.dialogRef.close(this.selectedName);
            }, err => {
              this.notificationService.warn(
                'Failed to add meeting'
              );
              this.dialogRef.close(this.selectedName);
            }
          );
        }
      }
    );
  }
}
