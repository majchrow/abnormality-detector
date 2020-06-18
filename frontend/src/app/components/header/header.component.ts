import {Component, OnInit} from '@angular/core';
import {Router} from '@angular/router';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit {

  public href = '';

  constructor(private router: Router) {
  }

  ngOnInit(): void {
    this.href = this.router.url;
  }

  navigate(value) {
    console.log();
    this.router.navigate([`/${value}`]);
  }

}
