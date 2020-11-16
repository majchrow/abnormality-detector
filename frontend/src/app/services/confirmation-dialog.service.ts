import {Injectable} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {MatConfirmDialogComponent} from '../components/shared/mat-confirm-dialog/mat-confirm-dialog.component';

@Injectable({
  providedIn: 'root'
})
export class ConfirmationDialogService {

  constructor(private dialog: MatDialog) {
  }

  private static getConfig(msg) {
    return {
      width: '390px',
      disableClose: true,
      position: {top: '10px'},
      data: {
        message: msg
      }
    };
  }

  openConfirmDialog(msg) {
    return this.dialog.open(MatConfirmDialogComponent, ConfirmationDialogService.getConfig(msg));
  }
}
