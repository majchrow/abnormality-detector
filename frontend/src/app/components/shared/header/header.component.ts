import {Component, OnInit} from '@angular/core';
import {Router} from '@angular/router';
import {Location} from '@angular/common';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit {

  public href = '';

  constructor(
    private location: Location,
    private router: Router) {
  }

  ngOnInit(): void {
    this.href = this.location.path().substr(1);
  }

  navigate(value) {
    this.router.navigate([`/${value}`]);
  }

}
